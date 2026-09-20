# Clarifications — JIRA-4821

| Question | Resolution | Source/owner | Effect on the change |
| --- | --- | --- | --- |
| What data classification applies? | Uploaded policies are confidential customer data. | `ticket/change-context.json`; Privacy Office | PRIV-003 and Canadian residency controls apply. |
| Which model route is approved? | The corporate Bedrock-backed AI gateway in `ca-central-1`. | AI Platform; `AI-004`; `ADR-013` | Direct public-provider access is prohibited without an exception. |
| Does retrieval already exist? | The project uses Bedrock Knowledge Bases behind the existing retrieval abstraction. | Project architect; `PR-02` | This change composes retrieval and generation; it does not add a vector database. |
| Are generated answers authoritative? | No. They are evidence-linked assistance for an authenticated underwriter. | Underwriting Risk | High-risk output needs pre-action human approval. |
| What happens when evidence is insufficient? | Return `insufficient_evidence` and do not call generation. | Product owner; `F-03` | Abstention is a testable invariant. |
| What evaluation evidence is required? | Retain labelled conformance cases, denominator, failures, and limitations. | AI Governance; `AI-012` | A deterministic evaluation suite is part of the change. |
| What does “adequate oversight” mean? | Tier 3 requires human approval before consequential use. | `AI-021-GUIDANCE`; Underwriting Risk | Approval is a separate gate, not a model decision. |
| What is the retention period? | Not established by the supplied sources. | Privacy Office | No new retention behavior is authorized by this change. |
