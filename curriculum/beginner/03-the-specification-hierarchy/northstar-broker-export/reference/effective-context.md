# Effective specification for AI-1937

**Resolution gate:** `READY`

| Control | Expected value | Governing IDs | Exception |
|---|---|---|---|
| AI-content disclosure | Required | AI-012 | — |
| Broker email delivery | Authorized broker only | F-002 | — |
| Data region | Approved Canadian regions | PRIV-018 | — |
| DLP inspection | Required before delivery | SEC-021 | — |
| Export format | PDF | F-001 | — |
| Model gateway | Enterprise Bedrock Gateway | AI-PLATFORM-007, ARCH-012 | — |
| Outbound email provider | Corporate Messaging Gateway | MSG-004 | — |
| Retention | 2,555 days for final approved communication | PRIV-030, RET-017 | EXC-009 |

## Recorded exclusions

- `PCI-002` — not applicable because `DATA-FLOW-1937` contains no payment-card data.
- `ARCH-004` — not applicable because its status is `superseded`; it remains decision history.
- `TICKET-MSG-001` — applicable feature input but rejected as authority where it conflicts with `MSG-004`.

## Conditions that must survive context compression

- Retain only the final approved broker communication.
- Delete intermediate model interactions after 30 days.
- Store the retained record encrypted.
- Enable access audit logging.

The generated context is a reviewed input to bounded implementation. It does not
grant release authority or prove policy conformance in production.
