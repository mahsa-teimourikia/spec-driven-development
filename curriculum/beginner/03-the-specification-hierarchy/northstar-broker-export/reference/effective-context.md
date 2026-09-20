# Effective specification for AI-1937

**Resolution gate:** `READY`

| Resource/control | Expected value | Governing IDs | Applicability evidence | Exception |
|---|---|---|---|---|
| Final broker record / AI disclosure | Required | AI-012 | FEATURE-SCOPE-1937 | — |
| Approved comparison / broker delivery | Authorized broker only | F-002 | JIRA-AI-1937 | — |
| Restricted customer data / region | Approved Canadian regions | PRIV-018 | DATA-CLASS-019; DATA-RESIDENCY-ASSESSMENT-004; DEPLOYMENT-ARCH-002 | — |
| Outbound broker email / DLP | Required before delivery | SEC-021 | DATA-FLOW-1937; FEATURE-SCOPE-1937 | — |
| Approved comparison / export format | PDF | F-001 | JIRA-AI-1937 | — |
| Inference request / model gateway | Enterprise Bedrock Gateway | AI-PLATFORM-007, ARCH-012 | DEPLOYMENT-ARCH-002; REPOSITORY-MANIFEST-001 | — |
| Outbound broker email / provider | Corporate Messaging Gateway | MSG-004 | FEATURE-SCOPE-1937 | — |
| Intermediate model interaction / retention | 30 days | PRIV-030 | DATA-CLASS-019; DATA-FLOW-1937 | — |
| Final approved broker communication / retention | 2,555 days | PRIV-031, RET-017 | DATA-CLASS-019; DATA-FLOW-1937; FEATURE-SCOPE-1937 | EXC-009 |

## Recorded exclusions

- `PCI-002` — not applicable because `DATA-FLOW-1937` contains no payment-card data.
- `ARCH-004` — not applicable because its status is `superseded`; it remains decision history.
- `TICKET-MSG-001` — applicable feature input but rejected as authority where it conflicts with `MSG-004`.

## Conditions that must survive context compression

- Retain only the final approved broker communication.
- Delete intermediate model interactions after 30 days.
- Store the retained record encrypted.
- Enable access audit logging.

The final-record control also retains `PRIV-031=30` and `RET-017=2555` as base
obligations and records `PRIV-030` as a related unaffected obligation for
explanatory traceability. The exception changes neither source policy. It changes
only its named requirement, modification, and scope; every other obligation
remains unchanged by default without requiring enumeration.

The generated context is a reviewed input to bounded implementation. It does not
grant release authority or prove policy conformance in production.
