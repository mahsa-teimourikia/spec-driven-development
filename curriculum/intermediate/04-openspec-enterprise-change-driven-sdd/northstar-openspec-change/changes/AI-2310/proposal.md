# Proposal — AI-2310 AI document-classification proposals

## Why

Manual classification delays underwriting and creates repetitive work. The change introduces non-authoritative AI proposals while preserving existing review authority.

## What changes

- supported broker documents may receive a classification proposal;
- ambiguous and unsupported results remain in manual processing;
- every proposal retains evidence and governing-context provenance; and
- document content remains untrusted data.

## Capabilities

### Modified capabilities

- `document-processing`

### New capabilities

None.

## Out of scope

- automatic authoritative classification;
- changes to authorization or review policy;
- replacement of extraction or review services; and
- production release.

## Impact

Document domain models, classification adapter, review-contract integration, evaluation, security tests, and operational documentation are affected.

