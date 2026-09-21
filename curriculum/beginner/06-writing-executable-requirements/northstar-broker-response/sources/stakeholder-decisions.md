# AI-2219 stakeholder decisions

Training fixture; identities and approvals are not authenticated.

| ID | Owner | Decision | Revision |
| --- | --- | --- | --- |
| DEC-BR-001 | Underwriting Domain | AI output is a proposal; trusted services determine status and mutate submissions. | 1 |
| DEC-BR-002 | Underwriting Domain | A conflicting value never automatically replaces a verified value. | 1 |
| DEC-BR-003 | Broker Identity | Only authenticated responses from a broker authorized for the submission enter processing. | 1 |
| DEC-BR-004 | Underwriting Operations | Supported non-conflicting field classes may be auto-applied only when policy explicitly permits it. | 1 |
| DEC-BR-005 | Product | Attachment extraction is outside Release 1; attachment-only evidence requires review. | 1 |
| DEC-BR-006 | Data Governance | Applied values retain response, span, requirement, model-version, and prior-value provenance. | 1 |

Automatic acceptance is not a model decision. Adding a supported field, changing a validation rule,
or widening the automatic-acceptance set requires an accountable source revision.
