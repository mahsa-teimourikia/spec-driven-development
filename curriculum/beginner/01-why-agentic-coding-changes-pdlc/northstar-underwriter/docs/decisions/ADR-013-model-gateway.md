# ADR-013 — Route generative-model access through the approved AI gateway

**Status:** Accepted  
**Owner:** AI Platform Architecture  
**Version:** 2.1  
**Commit:** `platform-adr-7f31c2a`

All production generative-model calls use the approved AI gateway. The gateway applies workload identity, provider allowlists, regional routing, redaction, rate limits, prompt-version headers, and audit correlation.

Direct provider SDK calls were rejected because application repositories would duplicate controls and accumulate long-lived provider credentials. An exception requires AI Platform Architecture and Privacy approval.
