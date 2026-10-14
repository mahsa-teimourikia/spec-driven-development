# Baseline Architecture

Revision: `ADR-058@3-training`

```text
Document intake
      ↓
Approved extraction service
      ↓
Document-processing domain
      ↓
Underwriting review workflow
```

The extraction service and review workflow already exist. A change may adapt their published contracts. Introducing a broker, database, model gateway, or authorization boundary is an architecture proposal that requires Architecture Council disposition.

