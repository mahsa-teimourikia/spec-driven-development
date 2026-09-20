# CONFLICT-001 — Direct model-provider access

- Sources: JIRA-4821 product comment; `PRIV-003` / control `C-02`; `AI-004` / control `P-02`; project decision `ADR-013`.
- Conflict: the ticket proposes direct OpenAI API use, while applicable enterprise and platform controls require an approved enterprise model route.
- Effective requirement: approved enterprise AI gateway in the Canadian region.
- Decision owner: AI Platform Architecture and Privacy Office; the product owner and coding agent cannot waive the controls.
- Implementation state before resolution: **BLOCKED**.
- Resolution used by this reference package: reject the ticket's implementation suggestion and retain the requested user outcome. Use the approved gateway. A direct-provider alternative would require a documented, scoped, expiring exception with compensating controls.

The ticket is not silently rewritten. This record preserves the rejected proposal, the governing sources, the decision owner, and the permissible exception path.
