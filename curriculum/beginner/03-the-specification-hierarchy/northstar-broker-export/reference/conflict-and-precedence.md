# Conflict and precedence resolution

## Authority resolution — outbound email provider

Both `MSG-004` and `TICKET-MSG-001` apply to AI-1937. They disagree about the
outbound email provider.

| Requirement | Layer | Authority | Expected value | Disposition |
|---|---|---|---|---|
| MSG-004 | Platform | Mandatory | `corporate_messaging_gateway` | Selected |
| TICKET-MSG-001 | Feature | Informal | `sendgrid_direct` | Rejected as authority |

Reason code: `HIGHER_AUTHORITY_WINS_NOT_GREATER_SPECIFICITY`.

The ticket is closer to the feature, but proximity and specificity do not grant
authority to replace a mandatory platform boundary.

## False conflict — different controlled resources

`PRIV-030` requires 30-day deletion of generated AI interactions containing PII.
`RET-017` requires seven-year retention of final broker underwriting
communications. Both are mandatory and applicable, but they govern different
resources:

| Requirement | Resource | Control | Value | Result |
|---|---|---|---:|---|
| PRIV-030 | Intermediate model interaction | Retention days | 30 | Effective |
| RET-017 | Final approved broker communication | Retention days | 2,555 | Effective |

There is no conflict. Treating `retention_days` as one global key would create a
false positive.

## Genuine conflict — same resource and lifecycle event

`PRIV-031` requires 30-day deletion of the final AI-generated broker communication.
`RET-017` requires seven-year retention of the same final broker record. Both are
mandatory, applicable, and in the `broker_record_retention` authority domain.
Layer order cannot decide which obligation disappears.

Without an independently owned resolution:

- **Conflict ID:** `CONFLICT-FINAL-APPROVED-BROKER-COMMUNICATION-RETENTION-DAYS`
- **Owners:** Privacy Office and Records Management
- **Agent action:** stop; attach applicability evidence and escalate
- **Implementation state:** blocked

The scoped `EXC-009` resolution is reviewed separately. It does not delete or
silently rewrite either policy, and it does not modify `PRIV-030`.
