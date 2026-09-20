# Approved clarifications

| ID | Question | Answer | Owner/source |
|---|---|---|---|
| CL-001 | Who may compare which documents? | An authenticated underwriter may select exactly two policy documents already authorized to that caller and tenant. | Product owner + SEC-014 |
| CL-002 | What does “accurate” mean for release evidence? | Each factual claim needs complete citations; each citation must support its proposition; each claim must be faithful to retrieved evidence; missing support produces an explicit abstention. | Underwriting domain owner + evaluation owner |
| CL-003 | Does human review apply, and what system control follows? | AI-021 requires authorized review before consequential use. The derived system control blocks decision-record entry unless a valid receipt linked to the comparison exists. | AI-021 owner + product owner |
| CL-004 | What latency is measured? | Use the p95 complete-response target and workload W1 defined by SLO-CMP-001. | Product + service owner |
| CL-005 | Is Redis required? | No. It is a design suggestion. Generated-response caching is deferred pending privacy, authorization, retention, freshness, and invalidation design. | Architecture owner |
