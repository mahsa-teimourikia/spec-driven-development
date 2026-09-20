# EXC-009 review

| Field | Reference finding |
|---|---|
| Requirement | PRIV-031 |
| Change/resource scope | AI-1937; final approved broker communication only |
| Control | `retention_days` |
| Permitted value for scoped records | `2555` days |
| Unaffected obligation | PRIV-030; intermediate model interactions remain 30 days |
| Owner | Privacy Office |
| Approver | Chief Privacy Officer |
| Approval-record locator | `APR-EXC-009-TRAINING` |
| Created | 2026-09-18 |
| Expires | 2027-09-30 |
| Status | Active |
| Source | `enterprise-exceptions:privacy/EXC-009.json@1.0-training#09ec009-training` |

## Conditions retained in the effective specification

1. Retain only the final approved broker communication.
2. Delete intermediate model interactions after 30 days.
3. Store the retained record encrypted.
4. Enable access audit logging.

The deterministic lab validates structure, scope, dates, provenance fields, and
conditions. It cannot authenticate the approver, prove that the approval record
exists in a trusted system, verify signature or digest binding, atomically consume
an approval, or establish legal sufficiency. Production enforcement needs those
trusted application controls.
