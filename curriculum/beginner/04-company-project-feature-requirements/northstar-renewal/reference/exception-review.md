# Exception review — EXC-014

- Governing requirement and revision: `AI-007@ai007v4-training`.
- Requester: Renewal Product.
- Authorized independent approver: AI Platform, the exception owner named by `AI-007`.
- Scope: project `underwriter-assistant`, feature `REQ-REN-001`.
- Modified obligation: `model_gateway=legacy_enterprise_gateway_proxy` instead
  of the base `enterprise_ai_gateway` value.
- Compensating conditions: restricted egress, preserved gateway audit events,
  and migration to the current gateway before expiry.
- Expiry: 2026-12-31.
- Local proof: required fields are present, the changed control exists in the
  parent, the parent revision matches, requester and approver differ, scope is
  non-empty, compensating conditions exist, and the record is not expired on
  the scenario date.
- Production boundary: the lab does not authenticate identities, signatures, protected storage, approval history, or compensating control operation.
