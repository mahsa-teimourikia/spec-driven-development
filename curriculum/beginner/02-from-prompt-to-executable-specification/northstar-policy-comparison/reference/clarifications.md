# Approved clarifications

| ID | Question | Answer | Owner/source |
|---|---|---|---|
| CL-001 | Who may compare which documents? | An authenticated underwriter may select exactly two policy documents already authorized to that caller and tenant. | Product owner + SEC-014 |
| CL-002 | What does “accurate” mean for release evidence? | Each comparison claim must cite supporting passages for the applicable side or sides. Missing support produces an explicit abstention, not an inferred difference. | Underwriting domain owner |
| CL-003 | Does human review apply? | AI-021 requires an authorized-underwriter receipt before a commercial comparison enters a consequential underwriting record. | AI-021 owner |
| CL-004 | What latency is measured? | Use the p95 complete-response target and workload W1 defined by SLO-CMP-001. | Product + service owner |
| CL-005 | Is Redis required? | No. It is a design suggestion. Generated-response caching is deferred pending privacy, authorization, retention, freshness, and invalidation design. | Architecture owner |
