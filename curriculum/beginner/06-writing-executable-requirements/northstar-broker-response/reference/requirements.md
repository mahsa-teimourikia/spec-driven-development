# AI-2219 normative requirements

The machine-readable metadata and full boundary fields live in
[`behavior-contract.json`](behavior-contract.json). This view is for review. The artifact roles in
that contract—not file format—define authority.

## REQ-BR-001 · safety obligation

An existing verified submission value SHALL NOT be automatically replaced by conflicting
broker-provided information.

This requirement owns the prohibition. `INV-BR-002` reinforces it across the declared population.

## REQ-BR-003 · event-driven

WHEN an authenticated broker response is received for a submission with outstanding information
requests, THE SYSTEM SHALL evaluate the response against those requests.

## REQ-BR-005 · unwanted behavior

IF a broker response contradicts an existing verified submission value, THEN THE SYSTEM SHALL
classify the proposal as `CONFLICTING`.

This requirement owns classification behavior. `DT-BR-001` elaborates it; it does not duplicate the
mutation prohibition owned by `REQ-BR-001`.

## REQ-BR-006 · optional feature

WHERE automatic acceptance is enabled for an approved field class, THE SYSTEM SHALL apply the
current field-acceptance policy before updating submission state.

## REQ-BR-007 · complex

WHILE a submission awaits broker information, WHEN an authenticated response provides a
non-conflicting value for an outstanding request, THE SYSTEM SHALL create a `ProposedUpdate` linked
to the source response.

## REQ-BR-008 · explicit elaboration

The system SHALL determine the disposition of a validated broker-provided value according to
`DT-BR-001`.

The table precondition requires a known verification state whenever an existing value is present.
Unknown verification metadata is routed to clarification before table evaluation.

## REQ-BR-020 and REQ-BR-021 · invalid values remain reviewable evidence

A `ProposedUpdate` SHALL satisfy current domain validation before authoritative application. A
proposal that fails domain validation is `REJECTED` and may still be surfaced—with its evidence and
reasons—for review or clarification. Reviewability does not create mutation eligibility.

## REQ-BR-037 · reviewed conflict resolution

WHEN a reviewed conflict is selected for replacement, THE SYSTEM SHALL require an unused, unexpired
approval receipt bound to the exact proposal digest, current submission revision, current
requirement-context digest, and `replace_verified_value` resolution before application.

## REQ-BR-031 · trust boundary

Model-generated status labels SHALL be treated as proposals and SHALL NOT authorize submission
mutation.
