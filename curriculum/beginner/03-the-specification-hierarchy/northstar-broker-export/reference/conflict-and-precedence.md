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

## Genuine conflict — retention

`PRIV-030` requires 30-day deletion of generated AI interactions containing PII.
`RET-017` requires seven-year retention of final broker underwriting
communications. Both are mandatory and applicable. Layer order cannot decide
which obligation disappears.

Without an independently owned resolution:

- **Conflict ID:** `CONFLICT-RETENTION-DAYS`
- **Owners:** Privacy Office and Records Management
- **Agent action:** stop; attach applicability evidence and escalate
- **Implementation state:** blocked

The scoped `EXC-009` resolution is reviewed separately. It does not delete or
silently rewrite either policy.
