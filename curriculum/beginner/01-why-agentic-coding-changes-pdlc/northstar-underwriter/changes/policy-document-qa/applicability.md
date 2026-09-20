# Applicability record — JIRA-4821

| Policy/control | Outcome | Evidence and evaluated condition | Owner/action if uncertain |
| --- | --- | --- | --- |
| PRIV-003 / C-02 | Applicable | Production + confidential customer data | Privacy Office |
| PRIV-011 / C-05 | Applicable | Confidential Canadian customer data | Privacy Office |
| AI-004 / P-02 | Applicable | Production generative-AI feature | AI Platform Architecture |
| AI-012 / C-04 | Applicable | Production AI release | AI Governance |
| AI-021 + guidance / D-01 | Applicable | Risk level is high; Tier 3 requires pre-action approval | Underwriting Risk |
| PCI-002 / C-90 | Not applicable | `feature_type=generative_ai`, not payment processing | Payment Security if scope changes |
| SEC-021 data egress | Uncertain in this fixture | The supplied registry has no independently versioned SEC-021 artifact | Security must classify any new external destination before implementation |

The unresolved SEC-021 artifact is not silently converted into permission. The accepted design introduces no new external destination and stays behind the already approved gateway. Any design that adds an egress destination must stop and obtain the authoritative rule.
