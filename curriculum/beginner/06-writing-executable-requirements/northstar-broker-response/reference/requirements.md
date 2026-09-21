# AI-2219 normative requirements

The machine-readable metadata and full boundary fields live in
[`behavior-contract.json`](behavior-contract.json). This view is for review. The artifact roles in
that contract—not file format—define authority.

## REQ-BR-003 · event-driven

WHEN an authenticated broker response is received for a submission with outstanding information
requests, THE SYSTEM SHALL evaluate the response against those requests.

## REQ-BR-005 · unwanted behavior

IF a broker response contradicts an existing verified submission value, THEN THE SYSTEM SHALL
classify the proposal as `CONFLICTING` and SHALL NOT modify the verified value.

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

## REQ-BR-031 · trust boundary

Model-generated status labels SHALL be treated as proposals and SHALL NOT authorize submission
mutation.
