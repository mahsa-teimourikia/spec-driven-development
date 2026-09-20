# Requirements — Policy document Q&A

## REQ-QA-001 — Authenticated question answering

The system SHALL allow an authenticated underwriter to ask a question about an uploaded policy document.

Scenario: authenticated request
GIVEN an underwriter authenticated through corporate SSO
WHEN the underwriter submits a non-empty question
THEN the service evaluates retrieved policy passages before generation.

## REQ-QA-002 — Supporting citations

Every answered response SHALL include at least one identifier for a supporting retrieved passage.

Scenario: supported answer
GIVEN one or more relevant authorized passages
WHEN the approved gateway returns an answer
THEN the response status is `answered` and citations contain the supporting passage identifiers.

## REQ-QA-003 — Insufficient evidence

WHEN no relevant supporting passage is available, THE SYSTEM SHALL return `insufficient_evidence`, an empty citation list, and no generated answer; it SHALL NOT call the model gateway.

## REQ-QA-004 — Approved model route and residency

Production generation SHALL use the approved AI gateway route in the Canadian region with a versioned prompt identifier.

## REQ-QA-005 — Human authority

Generated content SHALL be treated as assistance. High-risk use SHALL require an approval from an authorized Underwriting Risk role; the generation service SHALL NOT represent model output as approval.

## REQ-QA-006 — Evaluation evidence

The change SHALL retain labelled positive, negative, and boundary cases with explicit total cases, passed cases, safety violations, and known limitations.

## REQ-QA-007 — Observability without sensitive content

The application SHALL emit a structured completion event containing status, citation count, route, region, and prompt version, and SHALL NOT log the question, policy text, or generated answer.
