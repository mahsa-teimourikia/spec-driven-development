# Tasks — Policy document Q&A

| Task | Depends on | Requirement/control IDs | Evidence produced | Owner boundary |
| --- | --- | --- | --- | --- |
| T-01 Resolve applicability and conflict | — | C-02, C-04, C-05, C-90, P-02, D-01 | `applicability.md`, `conflict-record.md` | Policy owners decide exceptions |
| T-02 Specify behavior and stable contract | T-01 | F-01, F-02, F-03, PR-04 | `requirements.md` | Product owner approves behavior |
| T-03 Implement evidence-aware generation | T-02 | P-02, P-03, PR-01, PR-02, REQ-QA-001..004 | `policy_qa.py` | Agent edits feature branch only |
| T-04 Add redacted observability | T-03 | P-01, REQ-QA-007 | telemetry unit test | Platform owns production pipeline |
| T-05 Add independent tests and evaluation | T-03 | C-04, F-02, F-03, REQ-QA-006 | unit and evaluation reports | Evaluator is separate from candidate claims |
| T-06 Validate architecture and delivery | T-03 | C-01, C-03, P-04, PR-03, ADR-013 | architecture and policy checks | No production deployment authority |
| T-07 Verify approval receipts | T-01, T-05, T-06 | D-01, C-02 | `approvals.json` | Underwriting Risk and Privacy approve |
| T-08 Assemble evidence and decide merge | T-01..T-07 | all applicable IDs | gate report and evidence bundle | Production release remains separately blocked |
