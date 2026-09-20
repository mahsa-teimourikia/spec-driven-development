# Policy comparison specification v1

## Product intent

Help an authenticated underwriter compare coverage in two authorized policy documents while preserving evidence, authorization, and accountable human judgment.

## Requirements

### REQ-CMP-001 — Authorized selection

An authenticated underwriter can select exactly two policy documents inside the caller's tenant and document authorization boundary.

- **Owner:** Product owner
- **Source:** CL-001 and SEC-014
- **Scenario:** Given two authorized policies, when comparison starts, both identifiers are accepted. An unauthorized or cross-tenant identifier is rejected without returning document content.

### REQ-CMP-002 — Cited claims

Every comparison claim cites supporting passages from the applicable policy document or documents.

- **Owner:** Underwriting domain owner
- **Source:** CL-002
- **Scenario:** When a difference is displayed, the reviewer can inspect support for each side the claim describes.

### REQ-CMP-003 — Evidence-aware abstention

When evidence for either side is absent, the system reports insufficient evidence for that difference and does not infer one.

- **Owner:** Underwriting domain owner
- **Source:** CL-002
- **Scenario:** A one-sided retrieval result produces an explicit unsupported-side marker and no unsupported conclusion.

### REQ-CMP-004 — Consequential-use review

A commercial-policy comparison is reviewed by an authorized underwriter before it enters the underwriting decision record.

- **Owner:** Director of Underwriting Risk
- **Source:** AI-021
- **Scenario:** Without a valid reviewer receipt linked to the comparison, promotion to the decision record is denied.

### PERF-CMP-001 — Complete-response latency

The complete comparison response meets the approved first-release service objective.

- **Owners:** Product and service owner
- **Source/measure:** p95 ≤ 5 seconds under workload W1, measured as defined by SLO-CMP-001

### SEC-CMP-001 — Authorization isolation

Comparison retrieval and output never return content outside the authenticated tenant and document authorization boundary.

- **Owner:** Product Security
- **Source:** SEC-014
- **Scenario:** Cross-tenant and unauthorized-document probes return no content.

### OBS-CMP-001 — Safe traces

Comparison traces record request, requirement, evidence, model-route, and timing identifiers without policy text, retrieved passages, raw prompts, or personal data.

- **Owner:** Observability Platform
- **Source:** OBS-008

## Out of scope

- Automated underwriting decisions
- Comparison of more than two documents
- Generated-response caching
- Replacement of the existing document authorization service
